from __future__ import annotations
"""v1372 crash-safe campaign step checkpoints and exactly-once recovery assessment."""
import hashlib,json,os,re,tempfile
from pathlib import Path
from typing import Any,Mapping,Sequence
CONTRACT_VERSION='v1372.8';DIGEST=re.compile(r'^[a-f0-9]{64}$');ID=re.compile(r'^[A-Za-z0-9._-]{1,120}$')
STATES={'prepared','side_effect_recorded','completed'}
DENIED={'source_mutation_authorized':False,'project_mutation_authorized':False,'provider_contact_authorized':False,'network_authorized':False,'release_authorized':False,'approval_granted':False,'independent_authority_granted':False,'automatic_replay_authorized':False,'work_execution_authorized':False}
def _d(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def build_step_checkpoint(*,campaign_id:str,campaign_record_digest:str,step_id:str,attempt_id:str,state:str,operation_id:str='',result_digest:str='',mutating_side_effect:bool=False,result_confirmed:bool=False)->dict[str,Any]:
 if not ID.fullmatch(str(campaign_id or '')) or not ID.fullmatch(str(step_id or '')) or not ID.fullmatch(str(attempt_id or '')) or not DIGEST.fullmatch(str(campaign_record_digest or '')) or state not in STATES:return {'ok':False,'status':'step_checkpoint_lineage_invalid','runtime_written':False,**DENIED}
 op=str(operation_id or '');rd=str(result_digest or '')
 if state in {'side_effect_recorded','completed'} and (not ID.fullmatch(op) or not DIGEST.fullmatch(rd)):return {'ok':False,'status':'step_checkpoint_result_required','runtime_written':False,**DENIED}
 if state=='completed' and not result_confirmed:return {'ok':False,'status':'step_checkpoint_completion_unconfirmed','runtime_written':False,**DENIED}
 rec={'contract_version':CONTRACT_VERSION,'campaign_id':campaign_id,'campaign_record_digest':campaign_record_digest,'step_id_digest':_d(step_id),'attempt_id_digest':_d(attempt_id),'state':state,'operation_id_digest':_d(op) if op else '','result_digest':rd,'mutating_side_effect':bool(mutating_side_effect),'result_confirmed':bool(result_confirmed),'exactly_once_required':True,'content_free':True,'runtime_written':False,**DENIED};rec['checkpoint_digest']=_d(rec)
 return {'ok':True,'status':'step_checkpoint_ready','step_checkpoint':rec,'runtime_written':False,**DENIED}
def persist_step_checkpoint(*,runtime_root:str|Path,checkpoint:Mapping[str,Any])->dict[str,Any]:
 rec=dict(checkpoint);supplied=str(rec.pop('checkpoint_digest',''));valid=DIGEST.fullmatch(supplied or '') and supplied==_d(rec);rec['checkpoint_digest']=supplied
 if not valid:return {'ok':False,'status':'step_checkpoint_tampered','runtime_written':False,**DENIED}
 root=Path(runtime_root).expanduser().resolve();path=root/'campaign_checkpoints'/str(rec['campaign_id'])/(str(rec['step_id_digest'])+'.json')
 old={}
 if path.exists():
  try:old=json.loads(path.read_text())
  except Exception:return {'ok':False,'status':'step_checkpoint_existing_invalid','runtime_written':False,**DENIED}
  if old.get('checkpoint_digest')==supplied:return {'ok':True,'status':'step_checkpoint_already_stored','runtime_written':False,'checkpoint_digest':supplied,**DENIED}
  order={'prepared':0,'side_effect_recorded':1,'completed':2}
  if old.get('campaign_record_digest')!=rec.get('campaign_record_digest') or old.get('attempt_id_digest')!=rec.get('attempt_id_digest') or order.get(rec.get('state'),-1)<=order.get(old.get('state'),-1):return {'ok':False,'status':'step_checkpoint_non_monotonic','runtime_written':False,**DENIED}
 path.parent.mkdir(parents=True,exist_ok=True);payload=json.dumps(rec,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode();fd,tmp=tempfile.mkstemp(prefix='.step.',suffix='.tmp',dir=str(path.parent))
 try:
  with os.fdopen(fd,'wb') as h:h.write(payload);h.flush();os.fsync(h.fileno())
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
 return {'ok':True,'status':'step_checkpoint_stored','runtime_written':True,'checkpoint_digest':supplied,'stored_payload_digest':hashlib.sha256(payload).hexdigest(),**DENIED}
def assess_campaign_recovery(*,runtime_root:str|Path,campaign_id:str,campaign_record_digest:str,ordered_step_ids:Sequence[str])->dict[str,Any]:
 if not ID.fullmatch(str(campaign_id or '')) or not DIGEST.fullmatch(str(campaign_record_digest or '')) or not ordered_step_ids or len(ordered_step_ids)>256 or any(not ID.fullmatch(str(x)) for x in ordered_step_ids):return {'ok':False,'status':'campaign_recovery_request_invalid','work_resumed':False,**DENIED}
 root=Path(runtime_root).expanduser().resolve();rows=[];stop=None;resume=None
 for sid in ordered_step_ids:
  path=root/'campaign_checkpoints'/campaign_id/(_d(sid)+'.json')
  if not path.exists():resume=sid;rows.append({'step_id_digest':_d(sid),'state':'missing','decision':'resume_from_here'});break
  try:rec=json.loads(path.read_text())
  except Exception:stop='malformed_checkpoint';rows.append({'step_id_digest':_d(sid),'state':'invalid','decision':'stop'});break
  supplied=str(rec.pop('checkpoint_digest',''));valid=supplied==_d(rec);rec['checkpoint_digest']=supplied
  if not valid or rec.get('campaign_record_digest')!=campaign_record_digest:stop='checkpoint_lineage_invalid';rows.append({'step_id_digest':_d(sid),'state':'invalid','decision':'stop'});break
  state=rec.get('state')
  if state=='completed' and rec.get('result_confirmed') is True:rows.append({'step_id_digest':_d(sid),'state':'completed','decision':'skip_completed'});continue
  if state=='side_effect_recorded' and rec.get('mutating_side_effect') is True and rec.get('result_confirmed') is not True:stop='uncertain_mutating_side_effect';rows.append({'step_id_digest':_d(sid),'state':state,'decision':'stop_no_replay'});break
  resume=sid;rows.append({'step_id_digest':_d(sid),'state':state,'decision':'resume_from_here'});break
 if stop is None and resume is None:stop='campaign_steps_complete'
 status='recovery_blocked_uncertain_side_effect' if stop=='uncertain_mutating_side_effect' else ('recovery_blocked' if stop and stop!='campaign_steps_complete' else ('campaign_complete' if stop=='campaign_steps_complete' else 'recovery_ready'))
 rec={'contract_version':CONTRACT_VERSION,'campaign_id':campaign_id,'campaign_record_digest':campaign_record_digest,'step_count':len(ordered_step_ids),'decisions':rows,'resume_step_digest':_d(resume) if resume else '','stop_reason':stop or '','status':status,'completed_step_count':sum(x['decision']=='skip_completed' for x in rows),'duplicate_side_effect_replay':False,'work_resumed':False,'content_free':True,**DENIED};rec['recovery_digest']=_d(rec)
 return {'ok':status in {'recovery_ready','campaign_complete'},'status':status,'campaign_recovery':rec,'work_resumed':False,**DENIED}
def process_campaign_recovery_control(text:str,*,project_state=None,**_):
 if str(text or '').strip().lower() not in {'show campaign recovery','inspect campaign recovery','show crash recovery'}:return {'active':False}
 rec=dict((project_state or {}).get('campaign_recovery') or {});return {'active':True,'ok':bool(rec),'status':'campaign_recovery_found' if rec else 'campaign_recovery_missing','campaign_recovery':rec,'action_executed':False,**DENIED}
