from __future__ import annotations

"""v1498 bounded continuous-development campaign state machine.

Campaigns coordinate already-governed evidence. They do not contact providers,
edit source, authorize work, install candidates, or promote releases on their own.
"""

from copy import deepcopy
import hashlib, json
from typing import Any, Mapping

from development_authority import is_hex64, validate_operator_authorization

CONTRACT_VERSION='v1498.9'
STAGES=('discovered','compared','operator_selected','planned','workspace_authorized','implemented','verified','review_ready','stopped')


def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()

def new_campaign(*,campaign_id:str,candidate_id:str,baseline_source_digest:str)->dict[str,Any]:
 if not campaign_id or not candidate_id or len(str(baseline_source_digest))!=64:raise ValueError('campaign_identity_incomplete')
 row={'contract_version':CONTRACT_VERSION,'campaign_id':str(campaign_id),'candidate_id':str(candidate_id),'baseline_source_digest':str(baseline_source_digest),'stage':'discovered','processed_events':{},'evidence_digests':{},'operator_selected':False,'workspace_authorized':False,'stopped_reason':'','provider_contacted':False,'source_modified':False,'installation_authorized':False,'promotion_authorized':False,'content_free':True}
 row['state_digest']=_digest({k:v for k,v in row.items() if k!='state_digest'});return row

def apply_campaign_event(state:Mapping[str,Any],event:Mapping[str,Any])->dict[str,Any]:
 row=deepcopy(dict(state or {}));event_id=str(event.get('event_id') or '')
 if not event_id:return {'accepted':False,'reason':'event_id_required','state':row,'content_free':True}
 fingerprint=_digest(dict(event))
 prior=(row.get('processed_events') or {}).get(event_id)
 if prior:
  return {'accepted':prior==fingerprint,'duplicate':True,'reason':'duplicate_replay' if prior==fingerprint else 'event_id_collision','state':row,'content_free':True}
 current_digest=str(event.get('current_source_digest') or row.get('baseline_source_digest') or '')
 if current_digest!=str(row.get('baseline_source_digest') or ''):
  row['stage']='stopped';row['stopped_reason']='authoritative_source_changed';row.setdefault('processed_events',{})[event_id]=fingerprint;row['state_digest']=_digest({k:v for k,v in row.items() if k!='state_digest'});return {'accepted':False,'reason':'authoritative_source_changed','state':row,'content_free':True}
 action=str(event.get('action') or '')
 transitions={
  'record_comparison':('discovered','compared'),
  'operator_select':('compared','operator_selected'),
  'record_plan':('operator_selected','planned'),
  'authorize_workspace':('planned','workspace_authorized'),
  'record_implementation':('workspace_authorized','implemented'),
  'record_verification':('implemented','verified'),
  'record_review':('verified','review_ready'),
  'stop':(row.get('stage'),'stopped'),
 }
 if action not in transitions:return {'accepted':False,'reason':'unknown_campaign_action','state':row,'content_free':True}
 expected,next_stage=transitions[action]
 if row.get('stage')!=expected:return {'accepted':False,'reason':'stage_mismatch','state':row,'content_free':True}
 evidence=str(event.get('evidence_digest') or '')
 if action!='stop' and not is_hex64(evidence):return {'accepted':False,'reason':'evidence_digest_required','state':row,'content_free':True}
 if action in {'operator_select','authorize_workspace'}:
  stage='candidate_selection' if action=='operator_select' else 'workspace_preparation'
  authorization=validate_operator_authorization(event.get('operator_authorization_receipt'),stage=stage,subject_id=str(row.get('candidate_id') or ''),subject_digest=str(event.get('authority_digest') or evidence))
  if not authorization['ok']:return {'accepted':False,'reason':'operator_authority_required','state':row,'content_free':True}
 else:authorization={'authorization_id':'','receipt_digest':''}
 row['stage']=next_stage
 if action=='operator_select':row['operator_selected']=True
 if action=='authorize_workspace':row['workspace_authorized']=True
 if action in {'operator_select','authorize_workspace'}:
  row.setdefault('authorization_receipts',{})[action]={'authorization_id':authorization['authorization_id'],'receipt_digest':authorization['receipt_digest']}
 if evidence:row.setdefault('evidence_digests',{})[action]=evidence
 if action=='stop':row['stopped_reason']=str(event.get('reason') or 'operator_stop')[:100]
 row.setdefault('processed_events',{})[event_id]=fingerprint
 row['state_digest']=_digest({k:v for k,v in row.items() if k!='state_digest'})
 return {'accepted':True,'duplicate':False,'reason':'accepted','state':row,'content_free':True}

def campaign_public_projection(state:Mapping[str,Any])->dict[str,Any]:
 return {'contract_version':CONTRACT_VERSION,'campaign_id':state.get('campaign_id'),'candidate_id':state.get('candidate_id'),'stage':state.get('stage'),'processed_event_count':len(state.get('processed_events') or {}),'operator_selected':bool(state.get('operator_selected')),'workspace_authorized':bool(state.get('workspace_authorized')),'stopped_reason':state.get('stopped_reason'),'state_digest':state.get('state_digest'),'provider_contacted':False,'source_modified':False,'installation_authorized':False,'promotion_authorized':False,'content_free':True}

__all__=['CONTRACT_VERSION','new_campaign','apply_campaign_event','campaign_public_projection']
