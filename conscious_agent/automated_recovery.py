from __future__ import annotations
"""v1297.3-v1297.5 exact-baseline restoration after defined post-update failure."""
from pathlib import Path
from typing import Any,Mapping
from ordinary_chat_development_campaign import _proposal_lock
from governed_self_update_foundations import load_governed_self_update,validate_governed_self_update_packet,_runtime_root,_backup_path,_read_json,_write_json,_update_path,_record_digest,_digest
from governed_self_update import _current_state,_restore_backup
from automated_recovery_foundations import DENIED_AUTHORITY,TRIGGER_CODES,digest,valid_digest

CONTRACT_VERSION='v1297.5'

def evaluate_recovery_trigger(contract:Mapping[str,Any],trigger:Mapping[str,Any])->dict[str,Any]:
 violations=[]
 if trigger.get('recovery_contract_id')!=contract.get('recovery_contract_id') or trigger.get('recovery_contract_digest')!=contract.get('recovery_contract_digest'):violations.append('contract_identity_mismatch')
 if str(trigger.get('trigger_code') or '') not in TRIGGER_CODES:violations.append('undefined_trigger')
 if not valid_digest(trigger.get('trigger_digest')):violations.append('trigger_digest_missing')
 sealed_payload={k:v for k,v in trigger.items() if k!='trigger_digest' and k not in DENIED_AUTHORITY}
 if valid_digest(trigger.get('trigger_digest')) and trigger.get('trigger_digest')!=digest(sealed_payload):violations.append('trigger_digest_mismatch')
 if trigger.get('fresh') is not True:violations.append('stale_trigger')
 if trigger.get('source_state')!='candidate':violations.append('non_candidate_state')
 if int(trigger.get('private_finding_count') or 0)>0:violations.append('private_evidence_not_allowed')
 if float(trigger.get('observed_unix') or 0)<float(contract.get('prepared_unix') or 0) or float(trigger.get('observed_unix') or 0)>float(contract.get('expires_unix') or 0):violations.append('outside_observation_window')
 if any(bool(trigger.get(k)) for k in DENIED_AUTHORITY):violations.append('authority_expansion')
 return {"ok":not violations,"status":"automatic_recovery_required" if not violations else "automatic_recovery_blocked","violations":violations,"restore_target":"exact_pre_update_backup_only","operator_initiated_rollback_authorized":False,"content_free":True,"read_only":True,**DENIED_AUTHORITY}

def perform_automatic_recovery(contract:Mapping[str,Any],trigger:Mapping[str,Any],source_root:str|Path,*,runtime_root:str|Path)->dict[str,Any]:
 gate=evaluate_recovery_trigger(contract,trigger)
 if not gate['ok']:return {"ok":False,"status":"automatic_recovery_blocked","recovery_performed":False,"reason":"trigger_invalid",**DENIED_AUTHORITY}
 runtime=_runtime_root(runtime_root);source=Path(source_root).resolve(strict=True);update_id=str(contract.get('update_id') or '')
 with _proposal_lock('devc_'+update_id.split('_',1)[1],runtime):
  rec=load_governed_self_update(update_id,runtime_root=runtime)
  if rec.get('phase')=='rolled_back' and (rec.get('result') or {}).get('recovery_contract_id')==contract.get('recovery_contract_id'):
   return {**dict(rec.get('result') or {}),"operation_status":"restored"}
  if not rec or not validate_governed_self_update_packet(rec).get('ok'):return {"ok":False,"status":"automatic_recovery_update_record_invalid","recovery_performed":False,**DENIED_AUTHORITY}
  if rec.get('phase')!='applied_verified' or rec.get('authorization_consumed') is not True:return {"ok":False,"status":"automatic_recovery_update_not_eligible","recovery_performed":False,**DENIED_AUTHORITY}
  if rec.get('result_digest')!=contract.get('update_result_digest') or rec.get('source_manifest_digest')!=contract.get('baseline_source_digest') or rec.get('candidate_manifest_digest')!=contract.get('candidate_source_digest'):return {"ok":False,"status":"automatic_recovery_lineage_mismatch","recovery_performed":False,**DENIED_AUTHORITY}
  if _current_state(source,rec)!='candidate':return {"ok":False,"status":"automatic_recovery_source_conflict","recovery_performed":False,**DENIED_AUTHORITY}
  backup=_read_json(_backup_path(update_id,runtime))
  if not backup or backup.get('backup_digest')!=contract.get('backup_digest') or backup.get('source_manifest_digest')!=rec.get('source_manifest_digest'):return {"ok":False,"status":"automatic_recovery_backup_invalid","recovery_performed":False,**DENIED_AUTHORITY}
  try:_restore_backup(source,backup)
  except Exception:return {"ok":False,"status":"automatic_recovery_restore_failed","recovery_performed":False,**DENIED_AUTHORITY}
  restored=_current_state(source,rec)=='baseline'
  result={"ok":restored,"status":"automatic_recovery_complete" if restored else "automatic_recovery_verification_failed","update_id":update_id,"recovery_contract_id":contract.get('recovery_contract_id'),"trigger_code":trigger.get('trigger_code'),"recovery_performed":restored,"source_restored_to_baseline":restored,"candidate_reapplied":False,"arbitrary_content_written":False,"original_exact_update_authorization_was_consumed":True,"new_update_authorization_consumed":False,"operator_initiated_rollback_authorized":False,"active_source_modified":not restored,**DENIED_AUTHORITY}
  sealed=dict(rec);sealed.update({"contract_version":CONTRACT_VERSION,"phase":"rolled_back" if restored else "blocked","status":result['status'],"result":result,"result_digest":_digest(result),"active_source_modified":not restored,**DENIED_AUTHORITY});sealed['record_digest']=_record_digest(sealed);_write_json(_update_path(update_id,runtime),sealed)
  return result
