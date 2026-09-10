from __future__ import annotations

"""v1492 durable, content-free backlog and progress reasoning for dynamic candidates."""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib, json, os
from pathlib import Path
from typing import Any, Iterable, Mapping

from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from development_authority import is_hex64, validate_operator_authorization

CONTRACT_VERSION='v1492.9';SCHEMA_VERSION='1'
ACTIVE_STATES={'discovered','operator_selected','planned','workspace_authorized','implemented','verified','review_ready'}
TERMINAL_STATES={'installed','rejected','superseded','withdrawn'}
LEGAL_TRANSITIONS={
 'discovered':{'operator_selected','rejected','superseded','withdrawn'},
 'operator_selected':{'planned','rejected','superseded','withdrawn'},
 'planned':{'workspace_authorized','rejected','superseded','withdrawn'},
 'workspace_authorized':{'implemented','rejected','superseded','withdrawn'},
 'implemented':{'verified','rejected','superseded','withdrawn'},
 'verified':{'review_ready','rejected','superseded','withdrawn'},
 'review_ready':{'installed','rejected','superseded','withdrawn'},
}
AUTHORITY_STAGES={'operator_selected':'candidate_selection','workspace_authorized':'workspace_preparation','installed':'installation'}


def _now()->str:return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def _default()->dict[str,Any]:return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'items':[],'processed_events':[],'revision':0,'updated_at':'','content_free':True}

def default_backlog_path(runtime_root:str|Path|None=None)->Path:
 root=Path(runtime_root or os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()
 return root/'development'/'dynamic_candidate_backlog.json'

class DynamicDevelopmentBacklog:
 def __init__(self,runtime_root:str|Path|None=None):self.path=default_backlog_path(runtime_root)
 def _load(self):
  row=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items():row.setdefault(k,deepcopy(v))
  return row
 def snapshot(self):return deepcopy(self._load())
 def ingest_comparison(self,event_id:str,comparison:Mapping[str,Any])->dict[str,Any]:
  rows=[dict(x or {}) for x in comparison.get('ordered_comparison') or ()]
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {**deepcopy(prior['result']),'idempotent':True}
   existing={x.get('candidate_id'):x for x in s['items']}
   created=updated=0
   for rank,row in enumerate(rows,1):
    cid=str(row.get('candidate_id') or '')
    if not cid:continue
    payload={'candidate_id':cid,'comparison_digest':str(comparison.get('comparison_digest') or ''),'quality_score':float(row.get('quality_score') or 0.0),'quality_class':str(row.get('quality_class') or ''),'uncertainty':str(row.get('uncertainty') or ''),'rank':rank,'state':'discovered','operator_selected':False,'plan_digest':'','workspace_digest':'','verification_digest':'','review_digest':'','installation_digest':'','updated_at':_now(),'content_free':True}
    payload['item_digest']=_digest(payload)
    if cid in existing:
     old=existing[cid]
     if old.get('state') in TERMINAL_STATES:continue
     for k in ('comparison_digest','quality_score','quality_class','uncertainty','rank','updated_at','item_digest'):old[k]=payload[k]
     updated+=1
    else:s['items'].append(payload);existing[cid]=payload;created+=1
   result={'status':'backlog_ingested','created':created,'updated':updated,'item_count':len(s['items']),'content_free':True}
   s['processed_events'].append({'event_id':str(event_id)[:160],'result':deepcopy(result)});s['revision']+=1;s['updated_at']=_now();write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {**result,'idempotent':False}
 def transition(self,event_id:str,candidate_id:str,new_state:str,*,evidence_digest:str='',authority_digest:str='',operator_authorization_receipt:Mapping[str,Any]|None=None)->dict[str,Any]:
  if new_state not in ACTIVE_STATES|TERMINAL_STATES:raise ValueError('unsupported_backlog_state')
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {**deepcopy(prior['result']),'idempotent':True}
   row=next((x for x in s['items'] if x.get('candidate_id')==candidate_id),None)
   if not row:raise ValueError('candidate_not_in_backlog')
   current_state=str(row.get('state') or '')
   if new_state not in LEGAL_TRANSITIONS.get(current_state,set()):
    result={'status':'transition_blocked','candidate_id':candidate_id,'state':current_state,'reason':'illegal_state_transition','content_free':True}
   elif new_state not in TERMINAL_STATES and not is_hex64(evidence_digest):
    result={'status':'transition_blocked','candidate_id':candidate_id,'state':current_state,'reason':'evidence_digest_required','content_free':True}
   elif new_state=='installed' and not is_hex64(evidence_digest):
    result={'status':'transition_blocked','candidate_id':candidate_id,'state':current_state,'reason':'installation_evidence_required','content_free':True}
   else:
    stage=AUTHORITY_STAGES.get(new_state)
    authorization=validate_operator_authorization(operator_authorization_receipt,stage=stage,subject_id=candidate_id,subject_digest=str(authority_digest or evidence_digest)) if stage else {'ok':True,'authorization_id':'','receipt_digest':''}
    if not authorization['ok']:
     result={'status':'transition_blocked','candidate_id':candidate_id,'state':current_state,'reason':'operator_authority_required','content_free':True}
     s['processed_events'].append({'event_id':str(event_id)[:160],'result':deepcopy(result)});s['revision']+=1;s['updated_at']=_now();write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {**result,'idempotent':False}
    row['state']=new_state;row['operator_selected']=bool(row.get('operator_selected') or new_state=='operator_selected');row['updated_at']=_now()
    if evidence_digest:
     field={'planned':'plan_digest','workspace_authorized':'workspace_digest','verified':'verification_digest','review_ready':'review_digest','installed':'installation_digest'}.get(new_state)
     if field:row[field]=str(evidence_digest)
    if stage:
     row[f'{new_state}_authorization_id']=authorization['authorization_id'];row[f'{new_state}_authorization_receipt_digest']=authorization['receipt_digest']
    row['item_digest']=_digest({k:v for k,v in row.items() if k!='item_digest'});result={'status':'backlog_transitioned','candidate_id':candidate_id,'state':new_state,'content_free':True}
   s['processed_events'].append({'event_id':str(event_id)[:160],'result':deepcopy(result)});s['revision']+=1;s['updated_at']=_now();write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {**result,'idempotent':False}
 def progress_summary(self)->dict[str,Any]:
  s=self._load();counts={}
  for row in s['items']:counts[row.get('state')]=counts.get(row.get('state'),0)+1
  next_rows=sorted((x for x in s['items'] if x.get('state')=='discovered'),key=lambda x:(int(x.get('rank') or 9999),str(x.get('candidate_id'))))
  return {'contract_version':CONTRACT_VERSION,'item_count':len(s['items']),'state_counts':counts,'highest_review_candidate_id':str(next_rows[0].get('candidate_id') or '') if next_rows else '','selection_made_automatically':False,'operator_authority_required':True,'source_modified':False,'provider_contacted':False,'content_free':True,'backlog_digest':_digest([(x.get('candidate_id'),x.get('state'),x.get('item_digest')) for x in s['items']])}

__all__=['CONTRACT_VERSION','DynamicDevelopmentBacklog','default_backlog_path']
