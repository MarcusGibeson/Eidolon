from __future__ import annotations
"""v1375 durable, bounded long-task heartbeat and control evidence."""
import hashlib,json,re,time
from pathlib import Path
from typing import Any,Mapping
CONTRACT_VERSION="v1375.8"
DENIED={"process_stop_authorized":False,"timeout_budget_mutation_authorized":False,"project_mutation_authorized":False,"source_mutation_authorized":False,"release_authorized":False,"independent_authority_granted":False}
def _d(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def _root(runtime_root=None)->Path:
 p=Path(runtime_root or 'data')/'long_task_heartbeats';p.mkdir(parents=True,exist_ok=True);return p
def _path(campaign_digest,task_digest,runtime_root=None):return _root(runtime_root)/campaign_digest/task_digest/'heartbeat.json'
def _cancel_path(campaign_digest,task_digest,runtime_root=None):return _root(runtime_root)/campaign_digest/task_digest/'cancel.json'
def _load(path):
 if not path.exists():return None
 row=json.loads(path.read_text());dg=row.pop('record_digest',None)
 if dg!=_d(row):raise ValueError('heartbeat_tampered')
 row['record_digest']=dg;return row
def _save(path,row):
 path.parent.mkdir(parents=True,exist_ok=True);data=dict(row);data.pop('record_digest',None);data['record_digest']=_d(data);tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,sort_keys=True,separators=(',',':'))+'\n');tmp.replace(path);return data
def record_heartbeat(*,campaign_record_digest:str,task_id_digest:str,sequence:int,progress_units:int,total_units:int,observed_at_unix:int|None=None,state:str='running',minimum_interval_seconds:int=15,runtime_root=None)->dict[str,Any]:
 if not re.fullmatch(r'[a-f0-9]{64}',str(campaign_record_digest or '')) or not re.fullmatch(r'[a-f0-9]{64}',str(task_id_digest or '')):return {'ok':False,'status':'heartbeat_lineage_invalid','action_executed':False,**DENIED}
 if state not in {'running','completed','failed','cancelled'} or sequence<1 or total_units<1 or not(0<=progress_units<=total_units) or minimum_interval_seconds<1:return {'ok':False,'status':'heartbeat_fields_invalid','action_executed':False,**DENIED}
 now=int(time.time() if observed_at_unix is None else observed_at_unix);path=_path(campaign_record_digest,task_id_digest,runtime_root)
 try:prior=_load(path)
 except Exception:return {'ok':False,'status':'heartbeat_tampered','action_executed':False,**DENIED}
 if prior:
  if sequence<prior['sequence'] or progress_units<prior['progress_units'] or total_units!=prior['total_units']:return {'ok':False,'status':'heartbeat_regression_rejected','action_executed':False,**DENIED}
  if sequence==prior['sequence']:
   same=progress_units==prior['progress_units'] and state==prior['state'] and now==prior['observed_at_unix']
   return {'ok':same,'status':'heartbeat_duplicate' if same else 'heartbeat_sequence_conflict','heartbeat':prior if same else None,'action_executed':False,**DENIED}
  material=progress_units>prior['progress_units'] or state!=prior['state']
  if now-prior['observed_at_unix']<minimum_interval_seconds and not material:
   return {'ok':True,'status':'heartbeat_suppressed_no_material_change','heartbeat':prior,'persisted':False,'action_executed':False,**DENIED}
 row={'contract_version':CONTRACT_VERSION,'campaign_record_digest':campaign_record_digest,'task_id_digest':task_id_digest,'sequence':sequence,'progress_units':progress_units,'total_units':total_units,'progress_basis_points':progress_units*10000//total_units,'observed_at_unix':now,'state':state,'content_free':True,'raw_progress_text_persisted':False}
 saved=_save(path,row);return {'ok':True,'status':'heartbeat_recorded','heartbeat':saved,'persisted':True,'action_executed':False,**DENIED}
def request_task_cancellation(*,campaign_record_digest:str,task_id_digest:str,request_id:str,cancellation_authorized:bool,requested_at_unix:int|None=None,runtime_root=None)->dict[str,Any]:
 if not cancellation_authorized:return {'ok':False,'status':'cancellation_authority_required','action_executed':False,**DENIED}
 if not re.fullmatch(r'[a-f0-9]{64}',str(campaign_record_digest or '')) or not re.fullmatch(r'[a-f0-9]{64}',str(task_id_digest or '')) or not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,120}',str(request_id or '')):return {'ok':False,'status':'cancellation_request_invalid','action_executed':False,**DENIED}
 p=_cancel_path(campaign_record_digest,task_id_digest,runtime_root)
 row={'contract_version':CONTRACT_VERSION,'campaign_record_digest':campaign_record_digest,'task_id_digest':task_id_digest,'request_id_digest':_d(request_id),'requested_at_unix':int(time.time() if requested_at_unix is None else requested_at_unix),'cancellation_authorized':True,'process_stop_authorized':False,'content_free':True}
 try:prior=_load(p)
 except Exception:return {'ok':False,'status':'cancellation_record_tampered','action_executed':False,**DENIED}
 if prior:
  same=prior.get('request_id_digest')==row['request_id_digest']
  return {'ok':same,'status':'cancellation_duplicate' if same else 'cancellation_already_requested','cancellation':prior,'action_executed':False,**DENIED}
 saved=_save(p,row);return {'ok':True,'status':'cancellation_requested','cancellation':saved,'action_executed':False,**DENIED}
def assess_long_task(*,campaign_record_digest:str,task_id_digest:str,now_unix:int|None=None,silence_timeout_seconds:int=120,current_timeout_seconds:int=300,max_extension_seconds:int=300,extension_count:int=0,max_extensions:int=2,runtime_root=None)->dict[str,Any]:
 if silence_timeout_seconds<1 or current_timeout_seconds<1 or max_extension_seconds<0 or extension_count<0 or max_extensions<0:return {'ok':False,'status':'heartbeat_assessment_invalid','action_executed':False,**DENIED}
 try:hb=_load(_path(campaign_record_digest,task_id_digest,runtime_root));cancel=_load(_cancel_path(campaign_record_digest,task_id_digest,runtime_root))
 except Exception:return {'ok':False,'status':'heartbeat_evidence_tampered','action_executed':False,**DENIED}
 if not hb:return {'ok':False,'status':'heartbeat_missing','action_executed':False,**DENIED}
 now=int(time.time() if now_unix is None else now_unix);silence=max(0,now-hb['observed_at_unix']);terminal=hb['state'] in {'completed','failed','cancelled'};silent=(not terminal and silence>=silence_timeout_seconds)
 if cancel and not terminal:decision='cancel_requested'
 elif silent:decision='silence_detected'
 elif terminal:decision='terminal'
 else:decision='continue'
 extension=0
 if decision=='continue' and hb['progress_units']>0 and extension_count<max_extensions:extension=min(max_extension_seconds,max(0,current_timeout_seconds//2))
 rec={'contract_version':CONTRACT_VERSION,'heartbeat_record_digest':hb['record_digest'],'cancellation_record_digest':cancel['record_digest'] if cancel else None,'decision':decision,'silence_seconds':silence,'silence_detected':silent,'cancellation_requested':bool(cancel and not terminal),'timeout_extension_recommended_seconds':extension,'timeout_extension_applied':False,'progress_basis_points':hb['progress_basis_points'],'state':hb['state'],'content_free':True,'read_only':True,'action_executed':False,**DENIED};rec['record_digest']=_d(rec)
 return {'ok':True,'status':'long_task_assessed','long_task':rec,'action_executed':False,**DENIED}
def process_long_task_control(text:str,*,project_state=None,**_):
 if str(text or '').strip().lower() not in {'show task heartbeat','inspect task heartbeat','show long task status'}:return {'active':False}
 rec=dict((project_state or {}).get('long_task') or {})
 return {'active':True,'ok':bool(rec),'status':'long_task_found' if rec else 'long_task_missing','long_task':rec,'action_executed':False,**DENIED}
