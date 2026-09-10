from __future__ import annotations
"""v1371 durable content-minimized campaign records independent of chat rendering."""
import hashlib,json,os,re,tempfile
from pathlib import Path
from typing import Any,Mapping,Sequence
CONTRACT_VERSION='v1371.8'; DIGEST=re.compile(r'^[a-f0-9]{64}$'); ID=re.compile(r'^[A-Za-z0-9._-]{1,120}$')
STATES={'active','paused','blocked','completed','recovery_required'}
DENIED={'source_mutation_authorized':False,'project_mutation_authorized':False,'provider_contact_authorized':False,'network_authorized':False,'release_authorized':False,'approval_granted':False,'independent_authority_granted':False,'work_execution_authorized':False}
def _d(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def build_campaign_record(*,campaign_id:str,source_manifest_digest:str,workspace_digest:str,standing_grant_digest:str,standing_session_active:bool,goal_digest:str,plan_digest:str,budget_digest:str,current_step_id:str,total_steps:int,completed_steps:int,evidence_digests:Sequence[str]=(),state:str='active',recovery_state:str='clean',generation:int=1,prior_record_digest:str='')->dict[str,Any]:
 vals=[source_manifest_digest,workspace_digest,standing_grant_digest,goal_digest,plan_digest,budget_digest]
 if not ID.fullmatch(str(campaign_id or '')) or any(not DIGEST.fullmatch(str(x or '')) for x in vals):return {'ok':False,'status':'campaign_lineage_invalid','runtime_written':False,**DENIED}
 if not standing_session_active:return {'ok':False,'status':'campaign_standing_session_required','runtime_written':False,**DENIED}
 try: total=int(total_steps); done=int(completed_steps); gen=int(generation)
 except Exception:return {'ok':False,'status':'campaign_progress_invalid','runtime_written':False,**DENIED}
 if total<1 or done<0 or done>total or gen<1 or state not in STATES or recovery_state not in {'clean','checkpointed','recovery_required'}:return {'ok':False,'status':'campaign_progress_invalid','runtime_written':False,**DENIED}
 prior=str(prior_record_digest or '')
 if (gen==1 and prior) or (gen>1 and not DIGEST.fullmatch(prior)):return {'ok':False,'status':'campaign_generation_invalid','runtime_written':False,**DENIED}
 ev=list(evidence_digests)
 if len(ev)>256 or any(not DIGEST.fullmatch(str(x)) for x in ev):return {'ok':False,'status':'campaign_evidence_invalid','runtime_written':False,**DENIED}
 step=str(current_step_id or '')
 if not ID.fullmatch(step):return {'ok':False,'status':'campaign_step_invalid','runtime_written':False,**DENIED}
 rec={'contract_version':CONTRACT_VERSION,'campaign_id':campaign_id,'generation':gen,'prior_record_digest':prior,'source_manifest_digest':source_manifest_digest,'workspace_digest':workspace_digest,'standing_grant_digest':standing_grant_digest,'goal_digest':goal_digest,'plan_digest':plan_digest,'budget_digest':budget_digest,'current_step_digest':_d(step),'total_steps':total,'completed_steps':done,'remaining_steps':total-done,'evidence_count':len(ev),'evidence_set_digest':_d(sorted(ev)),'state':state,'recovery_state':recovery_state,'chat_history_required':False,'raw_goal_persisted':False,'raw_plan_persisted':False,'raw_evidence_persisted':False,'content_free':True,'runtime_record_only':True,'runtime_written':False,**DENIED};rec['record_digest']=_d(rec)
 return {'ok':True,'status':'campaign_record_ready','campaign_record':rec,'runtime_written':False,**DENIED}
def persist_campaign_record(*,runtime_root:str|Path,record:Mapping[str,Any])->dict[str,Any]:
 rec=dict(record);supplied=str(rec.pop('record_digest',''));valid=DIGEST.fullmatch(supplied or '') and supplied==_d(rec)
 rec['record_digest']=supplied
 if not valid or rec.get('runtime_record_only') is not True:return {'ok':False,'status':'campaign_record_tampered','runtime_written':False,**DENIED}
 root=Path(runtime_root).expanduser().resolve()
 if root.exists() and root.is_symlink():return {'ok':False,'status':'campaign_runtime_root_unsafe','runtime_written':False,**DENIED}
 path=root/'campaign_records'/str(rec['campaign_id'])/'record.json';old={}
 if path.exists():
  try: old=json.loads(path.read_text(encoding='utf-8'))
  except Exception:return {'ok':False,'status':'campaign_existing_record_invalid','runtime_written':False,**DENIED}
  if old.get('record_digest')==supplied:return {'ok':True,'status':'campaign_record_already_stored','runtime_written':False,'record_digest':supplied,'relative_runtime_path':f"campaign_records/{rec['campaign_id']}/record.json",**DENIED}
  if int(rec.get('generation') or 0)!=int(old.get('generation') or 0)+1 or rec.get('prior_record_digest')!=old.get('record_digest'):return {'ok':False,'status':'campaign_record_stale_generation','runtime_written':False,**DENIED}
 elif int(rec.get('generation') or 0)!=1:return {'ok':False,'status':'campaign_prior_generation_missing','runtime_written':False,**DENIED}
 payload=json.dumps(rec,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode();path.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(prefix='.record.',suffix='.tmp',dir=str(path.parent))
 try:
  with os.fdopen(fd,'wb') as h:h.write(payload);h.flush();os.fsync(h.fileno())
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
 return {'ok':True,'status':'campaign_record_stored','runtime_written':True,'record_digest':supplied,'stored_payload_digest':hashlib.sha256(payload).hexdigest(),'relative_runtime_path':f"campaign_records/{rec['campaign_id']}/record.json",**DENIED}
def load_campaign_record(*,runtime_root:str|Path,campaign_id:str,expected_record_digest:str)->dict[str,Any]:
 if not ID.fullmatch(str(campaign_id or '')) or not DIGEST.fullmatch(str(expected_record_digest or '')):return {'ok':False,'status':'campaign_load_request_invalid','record_loaded':False,**DENIED}
 path=Path(runtime_root).expanduser().resolve()/'campaign_records'/campaign_id/'record.json'
 try:rec=json.loads(path.read_text(encoding='utf-8'))
 except Exception:return {'ok':False,'status':'campaign_record_missing','record_loaded':False,**DENIED}
 supplied=str(rec.pop('record_digest',''));valid=supplied==expected_record_digest and supplied==_d(rec);rec['record_digest']=supplied
 if not valid:return {'ok':False,'status':'campaign_record_tampered','record_loaded':False,**DENIED}
 return {'ok':True,'status':'campaign_record_loaded','record_loaded':True,'campaign_record':rec,'chat_history_read':False,**DENIED}
def process_campaign_record_control(text:str,*,project_state=None,**_):
 if str(text or '').strip().lower() not in {'show campaign record','inspect campaign record','show campaign state'}:return {'active':False}
 rec=dict((project_state or {}).get('campaign_record') or {});return {'active':True,'ok':bool(rec),'status':'campaign_record_found' if rec else 'campaign_record_missing','campaign_record':rec,'action_executed':False,**DENIED}
